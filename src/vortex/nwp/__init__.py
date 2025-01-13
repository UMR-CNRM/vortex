"""
The NWP VORTEX extension package.
"""

# Recursive inclusion of packages with potential FootprintBase classes
from . import algo as algo
from . import data as data
from . import tools as tools
from . import syntax as syntax

#: No automatic export
__all__ = []

__tocinfoline__ = "The NWP VORTEX extension"
