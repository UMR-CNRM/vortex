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

__version__ = '1.8.4'
__prompt__ = 'Vortex v-' + __version__ + ':'

__nextversion__ = '1.9.0'
__tocinfoline__ = 'VORTEX core package'

__all__ = []

# Set vortex specific priorities for footprints usage

from bronx.fancies import loggers as bloggers

import footprints
footprints.priorities.set_before('debug', 'olive', 'oper')

# Set a root logging mechanism for vortex

#: Shortcut to Vortex's root logger
logger = bloggers.getLogger('vortex')

# Populate a fake proxy module with footprints shortcuts

from . import proxy
setup = footprints.config.get()
setup.add_proxy(proxy)
proxy.cat = footprints.proxy.cat
proxy.objects = footprints.proxy.objects

# Set a background environment and a root session

from . import tools
from . import sessions

rootenv = tools.env.Environment(active=True)

rs = sessions.get(active=True, topenv=rootenv, glove=sessions.getglove(), prompt=__prompt__)
if rs.system().systems_reload():
    rs.system(refill=True)
del rs

# Insert a dynamic callback so that any footprint resolution could check the current Glove


def vortexfpdefaults():
    """Return actual glove, according to current environment."""
    cur_session = sessions.current()
    return dict(
        glove=cur_session.glove,
        systemtarget=cur_session.sh.default_target
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

import bronx.stdtypes.date
from . import toolbox, algo, data

# Register proper vortex exit before the end of interpreter session


def complete():
    sessions.exit()
    import multiprocessing
    for kid in multiprocessing.active_children():
        logger.warning('Terminate active kid %s', str(kid))
        kid.terminate()
    print('Vortex', __version__, 'completed', '(', bronx.stdtypes.date.at_second().reallynice(), ')')


import atexit
atexit.register(complete)
del atexit, complete

print('Vortex', __version__, 'loaded', '(', bronx.stdtypes.date.at_second().reallynice(), ')')

del footprints
