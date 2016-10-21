#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
*Versatile Objects Rounded-up in a Toolbox for Environmental eXperiments*

VORTEX is a set of objects for basic resources handling in the context
of numerical weather prediction. Objects should be versatile enough to
be used either in an operational or research environment.

The user is provided with a standard interface for the description of
miscellaneaous resources (constants, climatological files, executable
models, etc.) with could be used as standalone objects or gathered inside
a logical layout defining the workflow of the experiment (configurations,
bunches, tasks, etc.).

Using the vortex modules implies the setting of a default session, as delivered
by the :mod:`vortex.sessions`. The current session could be changed and simultaneous
sessions could coexist.

Advanced users could access to specific classes of objects, but the use
of the very high level interface defined in the :mod:`vortex.toolbox` module is
strongly advised.
"""

__version__ = '0.10.3'
__prompt__  = 'Vortex v-' + __version__ + ':'

__all__ = []

# Force stdout to be an unbuffered stream
import os, sys
try:
    # With a standard Unix file descriptor
    sys.stdout = os.fdopen(sys.stdout.fileno(), 'w', 0)
except (IOError, AttributeError):
    try:
        # With an IOStream without file number
        sys.stdout.flush_interval = 0
    except AttributeError:
        sys.stderr.write('Unable to set an unbuffered stdout stream.')
del os
del sys

# Set vortex specific priorities for footprints usage

import footprints
footprints.priorities.set_before('debug', 'olive', 'oper')

# Set a root logging mechanism for vortex

#: Shortcut to Vortex's root logger
logger = footprints.loggers.getLogger('vortex')

footprints.loggers.defaultrootname = 'vortex'

# Populate a fake proxy module with footprints shortcuts

import proxy
setup = footprints.config.get()
setup.add_proxy(proxy)
proxy.cat = footprints.proxy.cat
proxy.objects = footprints.proxy.objects

# Set a background environment and a root session

import tools
import sessions

rootenv = tools.env.Environment(active=True)

rs = sessions.get(active=True, topenv=rootenv, glove=sessions.getglove(), prompt=__prompt__)
if rs.system().systems_reload():
    rs.system(refill=True)
del rs

# Insert a dynamic callback so that any footprint resolution could check the current Glove


def vortexfpdefaults():
    """Return actual glove, according to current environment."""
    return dict(
        glove = sessions.current().glove
    )

footprints.setup.callback = vortexfpdefaults

# Shorthands to sessions components

ticket = sessions.get
sh = sessions.system

# Specific toolbox exceptions


class VortexForceComplete(Exception):
    """Exception for handling fast exit mecanisms."""
    pass

# Load some superstars sub-packages

import toolbox, algo, data

# Register proper vortex exit before the end of interpreter session


def complete():
    sessions.exit()
    import multiprocessing
    for kid in multiprocessing.active_children():
        logger.warning('Terminate active kid %s', str(kid))
        kid.terminate()
    print 'Vortex', __version__, 'completed', '(', tools.date.at_second().reallynice(), ')'

import atexit
atexit.register(complete)
del atexit, complete

print 'Vortex', __version__, 'loaded', '(', tools.date.at_second().reallynice(), ')'
if __version__ != footprints.__version__:
    print '   ... with a non-matching footprints version (', footprints.__version__, ')'

del footprints
