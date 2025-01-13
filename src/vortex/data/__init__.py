"""
Abstract classes involved in data management within VORTEX.

Actual resources and custom providers should be defined in dedicated packages.
"""

from . import handlers as handlers
from . import resources as resources
from . import containers as containers
from . import contents as contents
from . import providers as providers
from . import executables as executables
from . import stores as stores
from . import geometries as geometries

#: No automatic export
__all__ = []

__tocinfoline__ = "Abstract classes involved in data management within VORTEX"
