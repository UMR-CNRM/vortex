#!/bin/env python
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

__version__ = '0.8.7'
__prompt__  = 'Vortex v-' + __version__+ ':'

__all__ = []

# Default logging mechanism

import logging
logging.basicConfig(
    format='[%(asctime)s][%(name)s][%(levelname)s]: %(message)s',
    datefmt='%Y/%d/%m-%H:%M:%S',
    level=logging.WARNING
)
logger = logging.getLogger('vortex')

# Set vortex specific priorities for footprints usage

import footprints
footprints.set_before('debug', 'olive', 'oper')

# Populate a fake proxy module with footprints shortcuts

import proxy
footprints.setup.popul(proxy)
proxy.cat = footprints.proxy.cat
proxy.objects = footprints.proxy.objects

# The module loader set the local logger to each module of the vortex packages

import loader

# Insert a dynamic callback so that any footprint resolution could check the current Glove

import tools
def getglove():
    return dict(glove = tools.env.current().glove)

footprints.setup.callback = getglove

# Set a background environment and a root session

import sessions
rootenv = tools.env.Environment(active=True)
rootenv.glove = sessions.glove()

rs = sessions.ticket(active=True, topenv=rootenv, glove=rootenv.glove, prompt=__prompt__)

if rs.system().systems_reload():
    rs.system(refill=True)

del rs

# Shorthands to sessions or footprints components

ticket = sessions.ticket
exit = sessions.exit
sh = sessions.system

# Load some superstars sub-packages

import toolbox, algo, data

# Register proper vortex exit before the end of interpreter session

import atexit
atexit.register(sessions.exit)
del atexit

