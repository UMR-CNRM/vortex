#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import io
import pwd

from datetime import datetime

from . import pools


def ask(**kw):
    """Build a proper request to Jeeves."""

    # default date is the actual pool stamp
    kw.setdefault('date', pools.timestamp())

    # build a proper json filename if requested
    kw.setdefault('jtag', kw.pop('jfile', None))

    # at least get a request object
    jr = pools.Request(**kw)

    # dump the json file if any
    if jr.jtag is not None:
        jr.dump()

    return jr

def ask_any(**kw):
    """Ask for some miscelaneous action..."""
    kw.setdefault('todo', 'foo')
    kw.setdefault('jtag', 'depot/' + kw['todo'])
    return ask(**kw)

def ask_debug():
    """Switch log verbosity to DEBUG level."""
    return ask(todo='level', data='debug')

def ask_level(value):
    """Switch log verbosity to sepcified level."""
    return ask(todo='level', data=str(value))

def ask_conf():
    """Wrapper for configuration display."""
    return ask(todo='show')

def ask_update(**kw):
    """Wrapper for configuration display."""
    return ask(todo='update', data=kw)

def ask_sleep(duration=30):
    """Make the server perfom a little nap."""
    return ask(todo='sleep', data=int(duration))

def ask_reload(*args):
    """Switch log verbosity to DEBUG level."""
    if not args:
        args = ('config', 'mkpools')
    return ask(todo='reload', data=args)

def ask_active(*args):
    """Swith on the specified pools."""
    return ask(todo='active', data=args)

def ask_mute(*args):
    """Swith off the specified pools."""
    return ask(todo='mute', data=args)