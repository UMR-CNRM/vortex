#!/bin/env python
# -*- coding: utf-8 -*-

r"""
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

__version__ = '0.6.25'

__all__ = []

import logging

logging.basicConfig(
    format='[%(asctime)s][%(name)s][%(levelname)s]: %(message)s',
    datefmt='%m/%d/%Y %H:%M:%S',
    level=logging.WARNING
)

logger = logging.getLogger('vortex')

import loader
import sessions, toolbox, algo, data, tools

# Set a background environment and a root session

rootenv = tools.env.Environment(active=True)
rootenv.glove = sessions.glove()

rs = sessions.ticket(active=True, topenv=rootenv, glove=rootenv.glove, prompt='Vortex v-'+__version__+':')

if rs.system().systems_reload():
    rs.system(refill=True)

del rs

# Shorthands to sessions components

ticket = sessions.ticket
exit = sessions.exit
sh = sessions.system

# Shorthands to the most useful class catalogs

components = algo.components.catalog
containers = data.containers.catalog
providers = data.providers.catalog
resources = data.resources.catalog
stores = data.stores.catalog
systems = tools.systems.catalog
