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

import atexit
import sys
import os

# importlib.metadata included in stdlib from 3.8 onwards.
# For older versions, import third-party importlib_metadata
if sys.version_info < (3, 8):
    import importlib_metadata
    import importlib

    importlib.metadata = importlib_metadata
else:
    import importlib.metadata

from bronx.fancies import loggers as bloggers
import bronx.stdtypes.date

import footprints

# Populate a fake proxy module with footprints shortcuts
from . import proxy, tools, sessions, config

# vortex user API
from .toolbox import input as input
from .toolbox import output as output
from .toolbox import executable as executable
from .toolbox import promise as promise
from .toolbox import diff as diff
from .toolbox import defaults as defaults
from .toolbox import algo as task

from . import nwp as nwp  # footprints import

__version__ = "2.1.0"
__prompt__ = "Vortex v-" + __version__ + ":"

__nextversion__ = "2.1.1"
__tocinfoline__ = "VORTEX core package"

__all__ = [
    "input",
    "output",
    "executable",
    "task",
    "promise",
    "diff",
]

# Set vortex specific priorities for footprints usage


footprints.priorities.set_before("debug", "olive", "oper")

# Set a root logging mechanism for vortex

#: Shortcut to Vortex's root logger
logger = bloggers.getLogger("vortex")

setup = footprints.config.get()
setup.add_proxy(proxy)
proxy.cat = footprints.proxy.cat
proxy.objects = footprints.proxy.objects

# Set a background environment and a root session
rootenv = tools.env.Environment(active=True)

rs = sessions.get(
    active=True, topenv=rootenv, glove=sessions.getglove(), prompt=__prompt__
)
if rs.system().systems_reload():
    rs.system(refill=True)
del rs

# Insert a dynamic callback so that any footprint resolution could check the current Glove


def vortexfpdefaults():
    """Return actual glove, according to current environment."""
    cur_session = sessions.current()
    return dict(
        glove=cur_session.glove, systemtarget=cur_session.sh.default_target
    )


footprints.setup.callback = vortexfpdefaults

# Shorthands to sessions components

ticket = sessions.get
sh = sessions.system

# If a config file can be found in current dir, load it else load .vortex.d/vortex.toml
if os.path.isfile("vortex.toml"):
    config.load_config("vortex.toml")
else:
    config.load_config(os.environ["HOME"] + "/.vortex.d/vortex.toml")

# Load some superstars sub-packages


# Now load plugins that have been installed with the
# 'vtx' entry point.  Order matters: since plugins
# will typically depend on objects defined in 'vortex'
# and 'vortex.nwp', these must be imported /before/
# loading plugins.
for plugin in importlib.metadata.entry_points(group="vtx"):
    plugin.load()
    print(f"Loaded plugin {plugin.name}")


# Register proper vortex exit before the end of interpreter session
def complete():
    sessions.exit()
    import multiprocessing

    for kid in multiprocessing.active_children():
        logger.warning("Terminate active kid %s", str(kid))
        kid.terminate()
    print(
        "Vortex",
        __version__,
        "completed",
        "(",
        bronx.stdtypes.date.at_second().reallynice(),
        ")",
    )


atexit.register(complete)
del atexit, complete

print(
    "Vortex",
    __version__,
    "loaded",
    "(",
    bronx.stdtypes.date.at_second().reallynice(),
    ")",
)

del footprints
